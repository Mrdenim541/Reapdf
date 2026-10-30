"""Validate reviewed rectangular cell merges without discarding covered text."""
from .engine import DocumentError


def validate(cells,spans):
    if spans is None:return {},{}
    if not isinstance(spans,list) or len(spans)>1500:raise DocumentError('Hasta 1500 combinaciones de celdas.')
    anchors={};covered={};occupied=set()
    for span in spans:
        if not isinstance(span,dict) or set(span)!={'row','column','rowspan','colspan'} or any(type(v) is not int for v in span.values()):raise DocumentError('Combinación de celdas no válida.')
        r,c,h,w=[span[k] for k in ['row','column','rowspan','colspan']]
        if min(r,c)<0 or min(h,w)<1 or h*w<2 or r+h>len(cells) or c+w>len(cells[0]):raise DocumentError('La combinación debe quedar dentro de la tabla y abarcar dos o más celdas.')
        region={(ri,ci) for ri in range(r,r+h) for ci in range(c,c+w)}
        if occupied&region:raise DocumentError('Las combinaciones de celdas no deben solaparse.')
        if any(cells[ri][ci] for ri,ci in region-{(r,c)}):raise DocumentError('Las celdas cubiertas deben estar vacías; reúne su contenido antes de combinar.')
        occupied.update(region);anchors[r,c]=span
        for key in region-{(r,c)}:covered[key]=(r,c)
    return anchors,covered
