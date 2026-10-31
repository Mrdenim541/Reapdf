"""Explicit empty table cells have structure, and deliberately no invented MCID."""
from .engine import DocumentError


def validate(cells,groups,selection,start):
    if cells is None:return []
    if not isinstance(cells,list) or len(cells)>500:raise DocumentError('Hasta 500 celdas vacías revisadas por documento.')
    result=[];seen=set()
    for index,cell in enumerate(cells):
        if not isinstance(cell,dict) or set(cell)-{'page','table','row','column','rowspan','colspan','role','scope'} or not {'page','table','row','column'}<=set(cell):raise DocumentError('Celda vacía no válida.')
        page=cell['page'];values={k:cell.get(k,1) for k in ['table','row','column','rowspan','colspan']};role=cell.get('role','TD');scope=cell.get('scope','Column')
        if type(page) is not int or any(type(v) is not int or not 1<=v<=100 for v in values.values()) or (page,values['table']) not in groups or role not in ['TH','TD'] or scope not in ['Row','Column','Both']:raise DocumentError('La celda vacía debe pertenecer a una tabla revisada y tener coordenadas válidas de 1 a 100.')
        key=(page,values['table'],values['row'],values['column'])
        if key in seen or any(c['row']==values['row'] and c['column']==values['column'] for c in groups[page,values['table']]):raise DocumentError('La celda vacía se repite o ya tiene contenido.')
        seen.add(key);identity='empty-'+str(index)
        selection[identity]={'role':role,'scope':scope,**values,'position':start+index,'merge_fragments':False}
        result.append({'id':identity,'page':page,'kind':'empty'})
    return result
