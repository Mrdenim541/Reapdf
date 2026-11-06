"""Bounded ordered packing by actual native PDF bytes, never by source ratio."""
from .engine import DocumentError


def size_limit(value,maximum):
    if type(value) is not int or not 1024<=value<=maximum:
        raise DocumentError('El tamaño máximo por PDF debe ser un número entero de bytes entre 1024 y 100 MB.')
    return value


def groups_by_bytes(count,atomic,limit,measure):
    # Related page sets may be nonconsecutive. Their complete interval is kept
    # together to preserve order without cutting an indivisible tagged object.
    blocked=set()
    for pages in atomic:
        if pages:blocked.update(range(min(pages),max(pages)))
    units=[];unit=[]
    for number in range(count):
        unit.append(number)
        if number not in blocked:units.append(unit);unit=[]
    groups=[];current=[]
    for unit in units:
        candidate=current+unit
        if measure(candidate)<=limit:current=candidate;continue
        if current:groups.append(current)
        if measure(unit)>limit:
            label=str(unit[0]+1) if len(unit)==1 else f'{unit[0]+1}–{unit[-1]+1}'
            raise DocumentError(f'La página o el grupo inseparable {label} supera el tamaño máximo. Aumenta el límite; no se reduce la calidad ni se entrega una división parcial.')
        current=unit
    if current:groups.append(current)
    return groups
