"""One-time Decimal calculations. Native values, no PDF JavaScript or formulas."""
from decimal import Decimal,localcontext,InvalidOperation,ROUND_HALF_UP
import re
from .engine import DocumentError,open_pdf,export_pdf
from .forms import form_model,prepare_fill
from .form_structure import expand_values


def calculate_fields(base,operations,calculation,validate_export=True):
    effective=operations;calculated_targets=set()
    if validate_export:
        export_pdf(base,operations)
        from .form_rules import resolve_rules
        effective,_,calculated_targets=resolve_rules(base,operations)
    if not isinstance(calculation,dict) or set(calculation)!={'operation','sources','target','decimal','places','empty_zero'}:raise DocumentError('Configuración de cálculo no válida.')
    kind=calculation['operation'];separator=calculation['decimal'];places=calculation['places'];refs=calculation['sources']
    if not isinstance(kind,str) or kind not in {'sum','product','average','min','max'} or separator not in ['dot','comma'] or type(places) is not int or not 0<=places<=6 or type(calculation['empty_zero']) is not bool or not isinstance(refs,list) or not 1<=len(refs)<=30:raise DocumentError('Elige una operación, de 1 a 30 fuentes y de 0 a 6 decimales.')
    with open_pdf(base) as doc:
        fields=form_model(doc)['fields'];rows={(r['page'],r['xref']):r for r in fields}
        def field(ref):
            if not isinstance(ref,dict) or set(ref)!={'page','xref'} or any(type(ref[k]) is not int for k in ref):raise DocumentError('Identidad de campo no válida.')
            row=rows.get((ref['page'],ref['xref']))
            if not row or row['kind']!='text' or not row['editable'] or row['multiline']:raise DocumentError('Usa campos de texto de una línea, editables y sin scripts.')
            return row
        sources=[field(ref) for ref in refs];target=field(calculation['target'])
        if target['group'] in calculated_targets:raise DocumentError('El destino está calculado por reglas del proyecto. Edita sus reglas o elige otro campo.')
        groups=[r['group'] for r in sources]
        if len(set(groups))!=len(groups) or target['group'] in groups:raise DocumentError('No repitas campos lógicos ni uses el destino como fuente.')
        previous=[v for op in effective if op.get('type')=='form_fill' for v in op['values']]
        expanded=expand_values(fields,previous) if previous else []
        values={(v['page'],v['xref']):v['value'] for v in expanded};numbers=[];inputs=[]
        for row in sources:
            value=values.get((row['page'],row['xref']),row['value'])
            if not isinstance(value,str):raise DocumentError('Un campo numérico no contiene texto compatible.')
            value=value.strip()
            if not value and calculation['empty_zero']:value='0'
            pattern=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)' if separator=='dot' else r'[+-]?(?:\d+(?:,\d*)?|,\d+)'
            if len(value)>50 or not re.fullmatch(pattern,value,flags=re.ASCII):raise DocumentError(f"El campo {row['label']} no es un número válido. Usa el separador elegido y no incluyas miles, moneda ni porcentajes.")
            number=Decimal(value.replace(',','.'))
            if abs(number)>Decimal('1e12'):raise DocumentError('Los valores absolutos no pueden superar un billón (10¹²).')
            numbers.append(number);inputs.append({'name':row['name'],'value':value})
        try:
            with localcontext() as context:
                context.prec=64
                if kind=='sum':result=sum(numbers,Decimal(0))
                elif kind=='average':result=sum(numbers,Decimal(0))/len(numbers)
                elif kind=='min':result=min(numbers)
                elif kind=='max':result=max(numbers)
                else:
                    result=Decimal(1)
                    for number in numbers:
                        result*=number
                        if abs(result)>Decimal('1e12'):raise DocumentError('El resultado intermedio supera 10¹².')
                if abs(result)>Decimal('1e12'):raise DocumentError('El resultado supera 10¹².')
                result=result.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP)
                if result==0:result=abs(result)
                text=format(result,f'.{places}f')
                if separator=='comma':text=text.replace('.',',')
        except InvalidOperation as exc:raise DocumentError('No se pudo calcular el resultado con la precisión elegida.') from exc
        incoming=expand_values(fields,[{'page':target['page'],'xref':target['xref'],'value':text}])
        merged={(v['page'],v['xref']):v for v in expanded}
        for entry in incoming:merged[(entry['page'],entry['xref'])]=entry
        changes=[v for key,v in merged.items() if v['value']!=rows[key]['value']]
        if changes:prepare_fill(doc,changes)
    next_ops=[op for op in operations if op.get('type')!='form_fill']
    if changes:next_ops.append({'type':'form_fill','page':0,'values':changes})
    if validate_export:export_pdf(base,next_ops)
    return next_ops,{'operation':kind,'inputs':inputs,'target':target['name'],'value':text,'decimal':separator,'places':places,'rounding':'ROUND_HALF_UP','automatic':False}
