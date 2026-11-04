"""One-based declarative page ranges, with optional positive strides."""
import re
from .engine import DocumentError


def parse(value,count):
    if type(count) is not int or not 1<=count<=500 or not isinstance(value,str) or not value.strip() or len(value)>2000:raise DocumentError('Selección de páginas no válida; usa hasta 2000 caracteres y de 1 a 500 páginas.')
    pages=[];seen=set()
    for part in value.split(','):
        match=re.fullmatch(r'\s*(\d+)(?:\s*-\s*(\d+)(?:\s*/\s*(\d+))?)?\s*',part)
        if not match:raise DocumentError('Usa páginas/rangos por comas y un salto opcional: 1-9/2, 2-8/2.')
        start=int(match[1]);end=int(match[2] or match[1]);step=int(match[3] or 1)
        if not 1<=start<=end<=count or not 1<=step<=count:raise DocumentError(f'Usa páginas y saltos entre 1 y {count}, con rangos crecientes.')
        for page in range(start-1,end,step):
            if page in seen:raise DocumentError('La selección contiene páginas repetidas.')
            seen.add(page);pages.append(page)
    return pages
