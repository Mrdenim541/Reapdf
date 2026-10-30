"""Reviewable complete partitions and Windows-compatible PDF output names."""
import re,unicodedata
from .engine import DocumentError,MAX_PAGES

RESERVED=re.compile(r'(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])\Z',re.I)


def filename(value):
    if not isinstance(value,str):raise DocumentError('Cada parte necesita un nombre de archivo.')
    value=unicodedata.normalize('NFC',value)
    if not value or value!=value.strip(' .') or any(c in '\\/:*?"<>|' or unicodedata.category(c).startswith('C') for c in value):raise DocumentError('Usa nombres sin rutas, controles ni caracteres \\ / : * ? " < > |, y sin espacios o puntos en los extremos.')
    if not value.lower().endswith('.pdf'):value+='.pdf'
    stem=value[:-4]
    if not stem or stem.endswith((' ','.')) or RESERVED.fullmatch(stem.split('.')[0]) or len(value)>120 or len(value.encode('utf-8'))>180:raise DocumentError('Nombre PDF vacío, reservado por Windows o demasiado largo (120 caracteres/180 bytes).')
    return value


def generated(value,index):
    text=unicodedata.normalize('NFC',str(value));text=''.join('_' if c in '\\/:*?"<>|' or unicodedata.category(c).startswith('C') else c for c in text).strip(' .') or 'Seccion'
    while len(text)>95 or len(text.encode('utf-8'))>150:text=text[:-1]
    return filename(f'{index:03d}-{text}')


def plan(doc,*,size=None,groups=None,names=None,bookmark_level=None):
    count=len(doc)
    if bookmark_level is not None:
        if type(bookmark_level) is not int or not 1<=bookmark_level<=10 or size is not None or groups is not None:raise DocumentError('Elige un nivel de marcadores de 1 a 10 sin mezclar bloques o grupos.')
        toc=doc.get_toc(False)
        if len(toc)>2000:raise DocumentError('El índice supera 2000 marcadores.')
        selected=[row for row in toc if row[0]==bookmark_level]
        if not selected:raise DocumentError('No hay marcadores en el nivel elegido.')
        if any(row[3].get('kind')!=1 or not 1<=row[2]<=count for row in selected):raise DocumentError('Los marcadores elegidos necesitan destinos de página internos.')
        starts=[row[2]-1 for row in selected];titles=[row[1] for row in selected]
        if any(b<=a for a,b in zip(starts,starts[1:])):raise DocumentError('Los marcadores deben avanzar por páginas distintas. Usa grupos manuales para resolver destinos repetidos o desordenados.')
        if starts[0]!=0:starts.insert(0,0);titles.insert(0,'Inicio')
        groups=[list(range(a,b)) for a,b in zip(starts,starts[1:]+[count])];defaults=[generated(title,i+1) for i,title in enumerate(titles)]
    elif groups is None:
        if type(size) is not int or not 1<=size<=count:raise DocumentError('El tamaño del bloque debe estar entre 1 y el número de páginas.')
        groups=[list(range(a,min(a+size,count))) for a in range(0,count,size)];defaults=[f'parte-{i+1:03d}.pdf' for i in range(len(groups))]
    else:
        if size is not None or not isinstance(groups,list) or not 1<=len(groups)<=MAX_PAGES:raise DocumentError('Configura bloques o grupos de páginas, sin mezclar ambos modos.')
        defaults=[f'parte-{i+1:03d}.pdf' for i in range(len(groups))]
    if not isinstance(groups,list) or not 1<=len(groups)<=MAX_PAGES:raise DocumentError('Selecciona de 1 a 500 partes.')
    for group in groups:
        if not isinstance(group,list) or not group or len(group)>count or any(type(p) is not int or not 0<=p<count for p in group) or len(set(group))!=len(group):raise DocumentError('Cada grupo necesita páginas válidas, sin repeticiones.')
    if sorted(p for group in groups for p in group)!=list(range(count)):raise DocumentError('Los grupos deben incluir cada página del documento exactamente una vez.')
    if names is None:names=defaults
    if not isinstance(names,list) or len(names)!=len(groups):raise DocumentError('Indica un nombre por cada archivo PDF de salida.')
    names=[filename(v) for v in names]
    if len(set(v.casefold() for v in names))!=len(names):raise DocumentError('Dos partes tienen el mismo nombre (también se comparan mayúsculas y acentos normalizados).')
    return {'parts':[{'name':name,'pages':group,'count':len(group)} for name,group in zip(names,groups)],'pages':count,'files':len(groups),'complete_partition':True,'source_modified':False,'bookmark_level':bookmark_level}
