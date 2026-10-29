"""Rectangular Word table merge plans; unsupported geometry keeps every cell."""
from .engine import DocumentError
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def tag(name):return '{'+W+'}'+name


def table_plan(table):
    rows=[];has_merge=False;fallback=None
    grid=table.find(tag('tblGrid'));columns=len(grid.findall(tag('gridCol'))) if grid is not None else None
    if columns is not None and not 1<=columns<=50:raise DocumentError('Una tabla Word necesita de 1 a 50 columnas.')
    for tr in table.findall(tag('tr')):
        props=tr.find(tag('trPr'))
        if props is not None and any(props.find(tag(k)) is not None for k in ['gridBefore','gridAfter']):fallback='filas con columnas omitidas'
        row=[];position=0;anchor=None
        for tc in tr.findall(tag('tc')):
            props=tc.find(tag('tcPr'));span=1;hm=vm=None
            if props is not None:
                node=props.find(tag('gridSpan'))
                if node is not None:
                    try:span=int(node.attrib.get(tag('val'),''))
                    except ValueError:raise DocumentError('Extensión de celda Word no válida.')
                    if not 1<=span<=50:raise DocumentError('Una celda Word puede combinar de 1 a 50 columnas.')
                    has_merge|=span>1
                for name in ['hMerge','vMerge']:
                    node=props.find(tag(name))
                    if node is not None:
                        value=node.attrib.get(tag('val'),'continue');has_merge=True
                        if value not in ['restart','continue']:fallback='marcas de combinación desconocidas'
                        if name=='hMerge':hm=value
                        else:vm=value
            cell={'nodes':[tc],'column':position,'colspan':span,'rowspan':1,'vertical':vm,'skip':False};position+=span
            if position>50:raise DocumentError('La tabla Word supera 50 columnas lógicas.')
            if hm=='continue':
                if anchor is None:fallback='continuación horizontal sin inicio';row.append(cell)
                else:
                    if anchor['vertical']!=vm:fallback='combinación horizontal/vertical contradictoria'
                    anchor['colspan']+=span;anchor['nodes'].append(tc)
            else:
                row.append(cell);anchor=cell if hm=='restart' else None
        if columns is None:columns=position
        if position!=columns:fallback='filas con cuadrículas distintas'
        rows.append(row)
    active={}
    for row in rows:
        next_active={}
        for cell in row:
            key=cell['column'],cell['colspan'];vm=cell['vertical']
            if vm=='restart':next_active[key]=cell
            elif vm=='continue':
                previous=active.get(key)
                if previous is None:fallback='continuación vertical sin inicio compatible'
                elif any((n.tag==tag('t') and (n.text or '').strip()) or n.tag in {tag('drawing'),tag('pict'),tag('tbl'),tag('fldSimple'),tag('fldChar')} for tc in cell['nodes'] for n in tc.iter()):fallback='contenido en una celda de continuación vertical'
                else:previous['rowspan']+=1;cell['skip']=True;next_active[key]=previous
        active=next_active
    if fallback:return None,has_merge,fallback
    return rows,has_merge,None
