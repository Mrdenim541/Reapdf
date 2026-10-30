"""Standard AFSimple_Calculate calls as bounded declarative PDF data, never JS."""
import re
from decimal import Decimal,localcontext,InvalidOperation
from .engine import DocumentError
from .form_actions import TOKEN,call,number,value as formatted_value


def parse(code):
    if not isinstance(code,str) or len(code)>4000:raise DocumentError('El cálculo PDF supera el límite de análisis.')
    m=re.fullmatch(r'\s*AFSimple_Calculate\s*\(\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')\s*,\s*(?:new\s+Array\s*\((.*?)\)|\[(.*?)\])\s*\)\s*;?\s*',code,re.S)
    if not m:raise DocumentError('El cálculo no es AFSimple_Calculate con nombres de campo explícitos.')
    operation=call('X('+m[1]+')')[1][0]
    if operation not in ['SUM','PRD','AVG','MIN','MAX']:raise DocumentError('Operación nativa de cálculo no admitida.')
    body=m[2] if m[2] is not None else m[3];names=[];at=0
    while at<len(body):
        token=TOKEN.match(body,at)
        if token is None or not token[1].startswith(('"',"'")):raise DocumentError('Las fuentes del cálculo necesitan nombres literales.')
        name=call('X('+token[1]+')')[1][0]
        if not 1<=len(name)<=200 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in name):raise DocumentError('Nombre de campo de cálculo no válido.')
        names.append(name);at=token.end()
        if len(names)>30:raise DocumentError('Hasta 30 fuentes por cálculo nativo.')
        if at==len(body):break
        if body[at]!=',':raise DocumentError('El cálculo contiene expresiones adicionales.')
        at+=1
        if not body[at:].strip():raise DocumentError('Fuente de cálculo vacía.')
    if not names or len(set(names))!=len(names):raise DocumentError('El cálculo necesita fuentes explícitas sin repetir.')
    return {'operation':operation,'sources':names}


def graph(doc,rows,allow_reorder=False):
    from .form_fields import _references
    order=[ref for ref,_ in _references(doc,doc.pdf_catalog(),'AcroForm/CO')]
    by_group={};names={}
    for row in rows:
        by_group.setdefault(row['group'],[]).append(row);names.setdefault(row['name'],set()).add(row['group'])
    targets={group:members[0]['native_rule'] for group,members in by_group.items() if members[0].get('native_rule')}
    if not targets and not order:return {'rules':[],'order':[],'order_issue':False}
    if len(targets)>50 or len(order)>50 or len(set(order))!=len(order) or set(order)!=set(targets):raise DocumentError('El orden CO debe incluir una vez cada campo calculado compatible, sin referencias adicionales.')
    def compatible(group,target=False):
        for row in by_group[group]:
            if not row.get('calculation_safe') or row['kind']!='text' or row['multiline'] or row.get('format',{} ) and row['format'].get('kind')=='date' or row['reason'] not in ['', 'Campo de solo lectura.']:raise DocumentError('Un cálculo depende de un campo no numérico o no compatible: '+row['name'])
    rules={}
    for target,definition in targets.items():
        compatible(target,True);sources=[]
        if any(r.get('native_rule')!=definition for r in by_group[target]):raise DocumentError('Las apariciones del resultado no comparten la misma acción de cálculo.')
        for name in definition['sources']:
            found=names.get(name,set())
            if len(found)!=1:raise DocumentError('Fuente de cálculo ausente o ambigua: '+name)
            group=next(iter(found));compatible(group);sources.append(group)
        rules[target]={'target':target,'name':by_group[target][0]['name'],**definition,'source_groups':sources}
    pending=set(targets);sorted_order=[]
    while pending:
        ready=[group for group in order if group in pending and not any(source in pending for source in rules[group]['source_groups'])]
        if not ready:raise DocumentError('Los cálculos nativos forman un ciclo, directo o indirecto.')
        sorted_order.extend(ready);pending.difference_update(ready)
    issue=sorted_order!=order
    if issue and not allow_reorder:raise DocumentError('El orden CO no respeta las dependencias de cálculo. Corrige su orden antes de rellenar.')
    return {'rules':[rules[g] for g in sorted_order],'order':order,'order_issue':issue}


def resolve(doc,model,values,recalculate=False):
    from .form_structure import expand_values
    rows=model['fields'];rules=model.get('native_calculations',[])
    if recalculate and not rules:raise DocumentError(model.get('native_calculation_error') or 'Este PDF no tiene cálculos nativos compatibles.')
    expanded=expand_values(rows,values) if values else []
    if not rules:return expanded,[]
    by_group={}
    for row in rows:by_group.setdefault(row['group'],[]).append(row)
    changed={row['group']:entry['value'] for entry in expanded for row in [next(r for r in rows if r['page']==entry['page'] and r['xref']==entry['xref'])]}
    reports=[]
    for rule in rules:
        inputs=[]
        for group in rule['source_groups']:
            row=by_group[group][0];text=changed.get(group,row['value'])
            if not isinstance(text,str):raise DocumentError('La fuente numérica no contiene texto: '+row['name'])
            inputs.append(Decimal(0) if not text.strip() else number(text,row.get('format',{}).get('separator',1) if row.get('format') else 1))
        try:
            with localcontext() as ctx:
                ctx.prec=34;kind=rule['operation']
                if kind=='SUM':result=sum(inputs,Decimal(0))
                elif kind=='AVG':result=sum(inputs,Decimal(0))/len(inputs)
                elif kind=='MIN':result=min(inputs)
                elif kind=='MAX':result=max(inputs)
                else:
                    result=Decimal(1)
                    for operand in inputs:
                        result*=operand
                        if abs(result)>Decimal('1e12'):raise DocumentError('El producto nativo intermedio supera 10¹².')
                if not result.is_finite() or abs(result)>Decimal('1e12'):raise DocumentError('El resultado del cálculo nativo supera 10¹².')
                canonical=format(result.normalize(),'f') if result else '0'
        except InvalidOperation as exc:raise DocumentError('El cálculo nativo no tiene un resultado compatible.') from exc
        target=by_group[rule['target']][0];text=canonical
        if target.get('format') and target['format'].get('separator',1) in [2,3]:text=text.replace('.',',')
        if target.get('format'):formatted_value(target['format'],text)
        changed[rule['target']]=text;reports.append({'target':target['name'],'operation':rule['operation'],'sources':rule['sources'],'value':text,'native':True})
    return [{'page':r['page'],'xref':r['xref'],'value':changed[r['group']]} for r in rows if r['group'] in changed],reports


def repair_order(base,operations):
    from .engine import open_pdf,export_pdf
    from .document_tools import editable
    from .forms import form_model
    from .form_fields import set_form_key
    import pymupdf as f
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        model=form_model(doc,allow_reorder=True)
        if model.get('native_calculation_error') or not model.get('native_calculations'):raise DocumentError(model.get('native_calculation_error') or 'No hay cálculos compatibles cuyo orden se pueda corregir.')
        rules=model['native_calculations'];before=[r for r in model['native_calculation_order']];after=[r['target'] for r in rules]
        if before==after:raise DocumentError('El orden de cálculo ya respeta sus dependencias.')
        set_form_key(doc,'CO','['+' '.join(f'{ref} 0 R' for ref in after)+']');data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(data) as doc:
        check=form_model(doc)
        if check.get('native_calculation_error'):raise DocumentError('No se pudo verificar el nuevo orden de cálculo.')
    return data,{'corrected':True,'order':[r['name'] for r in rules]}
