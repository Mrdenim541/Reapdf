"""Declarative calculations in Reapdf projects; exported PDFs contain values."""
from .engine import DocumentError,open_pdf
from .forms import form_model


def resolve_rules(base,operations):
    rules_ops=[op for op in operations if isinstance(op,dict) and op.get('type')=='form_rules']
    if not rules_ops:return operations,[],set()
    if len(rules_ops)!=1:raise DocumentError('Solo se admite una configuración de cálculos automáticos.')
    op=rules_ops[0]
    if set(op)!={'type','page','version','rules'} or op['page']!=0 or type(op['page']) is not int or type(op['version']) is not int or op['version']!=1 or not isinstance(op['rules'],list) or not 1<=len(op['rules'])<=10:raise DocumentError('Configura de 1 a 10 reglas de cálculo compatibles.')
    rules=op['rules']
    with open_pdf(base) as doc:
        rows=form_model(doc)['fields'];fields={(r['page'],r['xref']):r for r in rows}
    def group(ref):
        if not isinstance(ref,dict) or set(ref)!={'page','xref'} or any(type(v) is not int for v in ref.values()):raise DocumentError('Referencia de cálculo no válida.')
        row=fields.get((ref['page'],ref['xref']))
        if not row or not row['editable'] or row['kind']!='text' or row['multiline']:raise DocumentError('Las reglas necesitan campos de texto de una línea, editables y sin scripts.')
        return row['group']
    targets=[];sources=[]
    for rule in rules:
        if not isinstance(rule,dict) or not isinstance(rule.get('sources'),list) or not 1<=len(rule['sources'])<=30:raise DocumentError('Fuentes de cálculo no válidas.')
        targets.append(group(rule.get('target')));sources.append({group(ref) for ref in rule['sources']})
    if len(set(targets))!=len(targets):raise DocumentError('Un campo no puede tener dos reglas de cálculo.')
    remaining=set(range(len(rules)));ordered=[]
    while remaining:
        available=[i for i in sorted(remaining) if not any(targets[j] in sources[i] for j in remaining)]
        if not available:raise DocumentError('Las reglas forman un ciclo. Un destino no puede depender de sí mismo, directa o indirectamente.')
        ordered.extend(available);remaining.difference_update(available)
    # Existing non-calculation edits are rendered by the caller once. Numeric
    # evaluation needs only base widgets and pending fills, never other edits.
    from .form_calculations import calculate_fields
    fills=[v for v in operations if isinstance(v,dict) and v.get('type')=='form_fill']
    if len(fills)>1:raise DocumentError('Solo se admite una configuración de formulario.')
    current=fills;reports=[]
    for index in ordered:
        try:current,report=calculate_fields(base,current,rules[index],validate_export=False)
        except DocumentError as exc:raise DocumentError(f'Regla {index+1}: {exc}') from exc
        reports.append({'rule':index+1,**report,'automatic':True})
    other=[v for v in operations if not isinstance(v,dict) or v.get('type') not in {'form_fill','form_rules'}]
    return other+current,reports,set(targets)


def remap_rules(base,operations,result,page_map=None,renamed=None):
    """Keep declarative rules across validated field and page transformations.

    PDF xrefs change on save. Match logical fields by unique full name and
    surviving page membership, never by old xref or label alone.
    """
    from copy import deepcopy
    raw=[op for op in operations if isinstance(op,dict) and op.get('type')=='form_rules']
    if not raw:return []
    resolve_rules(base,operations)  # Validate the old graph before mapping it.
    with open_pdf(base) as doc:old=form_model(doc)['fields']
    with open_pdf(result) as doc:new=form_model(doc)['fields']
    if page_map is None:
        with open_pdf(base) as doc:page_map={i:i for i in range(len(doc))}
    renamed=renamed or {}
    old_refs={(row['page'],row['xref']):row for row in old}
    mapped=deepcopy(raw[0]);cache={}
    def remap(ref):
        row=old_refs[(ref['page'],ref['xref'])];group=row['group']
        if group not in cache:
            survivors=[r for r in old if r['group']==group and r['page'] in page_map]
            candidates=[r for r in new if r['name']==renamed.get(row['name'],row['name'])]
            from collections import Counter
            expected=Counter(page_map[r['page']] for r in survivors)
            actual=Counter(r['page'] for r in candidates)
            if not survivors:
                raise DocumentError(f'El cambio eliminaría el campo «{row["name"]}», necesario para un cálculo automático. Conserva su página o retira la regla antes de continuar.')
            if actual!=expected or len({r['group'] for r in candidates})!=1 or any(not r['editable'] or r['kind']!='text' or r['multiline'] for r in candidates):
                raise DocumentError(f'No se puede conservar con certeza el cálculo del campo «{row["name"]}». No se aplicó el cambio.')
            selected=next((r for r in candidates if r['page']==page_map.get(row['page'])),candidates[0])
            cache[group]={'page':selected['page'],'xref':selected['xref']}
        return deepcopy(cache[group])
    for rule in mapped['rules']:
        rule['sources']=[remap(ref) for ref in rule['sources']];rule['target']=remap(rule['target'])
    # A final calculation/render rejects changed types, ambiguity and values
    # that no longer fit. The caller stores the version only after this succeeds.
    from .engine import export_pdf
    export_pdf(result,[mapped])
    return [mapped]


def remap_organized_rules(base,operations,result,pages):
    return remap_rules(base,operations,result,{row['page']:index for index,row in enumerate(pages)})


def splice_page_map(base,position,removed,added):
    """Map only surviving original pages; imported copies get no old identity."""
    with open_pdf(base) as doc:count=len(doc)
    return {i:i if i<position else i+added-removed for i in range(count) if not position<=i<position+removed}


def remap_field_rules(base,operations,result,number,xref,changes):
    if not any(isinstance(op,dict) and op.get('type')=='form_rules' for op in operations):return []
    renamed={}
    if changes and 'partial_name' in changes:
        from .engine import export_pdf
        # The properties inspector and editor address the materialized version.
        # Filling can renumber xrefs; its unique logical name links to the base.
        with open_pdf(export_pdf(base,operations)) as doc:
            row=next((r for r in form_model(doc)['fields'] if r['page']==number and r['xref']==xref),None)
        if row is None:raise DocumentError('El campo no pertenece al documento base; no se reasignan sus cálculos.')
        prefix=row['name'].rsplit('.',1)[0]+'.' if '.' in row['name'] else ''
        renamed[row['name']]=prefix+changes['partial_name']
    return remap_rules(base,operations,result,renamed=renamed)
