"""Bounded section segmentation and independent page geometry for Word imports."""
from copy import deepcopy
from xml.etree import ElementTree as E
import pymupdf as f
from .engine import DocumentError
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def tag(name):return '{'+W+'}'+name


def sections(body,paper):
    result=[];nodes=[];inherited={}
    def append(properties):
        nonlocal nodes
        if len(result)>=50:raise DocumentError('Hasta 50 secciones Word por importación.')
        section=deepcopy(properties) if properties is not None else E.Element(tag('sectPr'))
        kind=section.find(tag('type'));kind=kind.attrib.get(tag('val'),'nextPage') if kind is not None else 'nextPage'
        if result and kind!='nextPage':raise DocumentError('Esta importación admite secciones con salto a página siguiente. Convierte los saltos continuos, de columna, pares o impares antes de importar.')
        # Missing header/footer references link to the preceding section, by variant.
        own={}
        for name in ['headerReference','footerReference']:
            for ref in section.findall(tag(name)):
                key=name,ref.attrib.get(tag('type'),'default')
                if key in own:raise DocumentError('Referencias de sección Word repetidas.')
                own[key]=ref
        for key,ref in inherited.items():
            if key not in own:section.append(deepcopy(ref))
        inherited.update({key:deepcopy(ref) for key,ref in own.items()})
        size=f.paper_size('a4' if paper=='source' else paper);margins=[36.,36.,36.,36.]
        if paper=='source':
            pg=section.find(tag('pgSz'));mar=section.find(tag('pgMar'))
            try:
                if pg is not None:size=[int(pg.attrib[tag(k)])/20 for k in ['w','h']]
                if mar is not None:margins=[int(mar.attrib[tag(k)])/20 for k in ['left','top','right','bottom']]
            except (ValueError,KeyError):raise DocumentError('Tamaño o márgenes de Word no válidos.')
        if min(size)<144 or max(size)>1584 or min(margins)<0 or size[0]-margins[0]-margins[2]<72 or size[1]-margins[1]-margins[3]<72:raise DocumentError('Tamaño de Word fuera de límites o sin espacio suficiente para contenido.')
        result.append({'properties':section,'nodes':nodes,'size':size,'margins':margins});nodes=[]
    for node in body:
        if node.tag==tag('sectPr'):
            append(node)
        else:
            nodes.append(node)
            if node.tag==tag('p'):
                props=node.find(tag('pPr'));end=props.find(tag('sectPr')) if props is not None else None
                if end is not None:append(end)
    if nodes or not result:append(None)
    return result
