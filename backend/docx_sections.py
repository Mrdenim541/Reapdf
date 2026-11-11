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
        if result and kind not in ['nextPage','oddPage','evenPage','continuous']:raise DocumentError('Esta importación admite secciones con salto a página siguiente, par, impar o continuas compatibles. Los saltos de sección a columna requieren otro tratamiento.')
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
        from .docx_columns import parse as columns
        result.append({'properties':section,'nodes':nodes,'size':size,'margins':margins,'columns':columns(section,size[0]-margins[0]-margins[2]),'break':kind,'trailing_blanks':0});nodes=[]
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


def continuous_groups(segments,package,parse_xml):
    """Join identical-layout continuous sections, keeping source identities.

    Geometry-changing continuous sections need balancing and remain protected.
    """
    def key(node):
        children=[key(c) for c in node if c.tag not in [tag('type'),tag('cols')]]
        return node.tag,tuple(sorted(node.attrib.items())),(node.text or '').strip(),tuple(sorted(children) if node.tag==tag('sectPr') else children)
    result=[];section_pages=None
    for index,segment in enumerate(segments):
        segment['source_sections']=[index+1];segment['flow_parts']=[{'nodes':list(segment['nodes']),'columns':segment['columns'],'source_sections':[index+1]}]
        if not result or segment['break']!='continuous':result.append(segment);continue
        previous=result[-1];a=previous['properties'];b=segment['properties']
        unsafe=['pgNumType','titlePg','footnotePr','endnotePr']
        has_notes=any(n.tag in [tag('footnoteReference'),tag('endnoteReference')] for s in [previous,segment] for node in s['nodes'] for n in node.iter())
        if section_pages is None:
            section_pages=False
            for name,value in package.items():
                if name.endswith('.xml') and name.startswith(('word/header','word/footer')):
                    root=parse_xml(value);content=''.join(list(root.itertext())+[v for node in root.iter() for v in node.attrib.values()]).upper()
                    section_pages=section_pages or 'SECTIONPAGES' in content
        if previous['size']!=segment['size'] or previous['margins']!=segment['margins'] or key(a)!=key(b) or has_notes or section_pages or any(a.find(tag(k)) is not None or b.find(tag(k)) is not None for k in unsafe):
            raise DocumentError('Las secciones continuas con cambios de geometría, encabezados, numeración o notas necesitan otro tratamiento; usa página siguiente para este perfil compatible.')
        previous['nodes'].extend(segment['nodes']);previous['source_sections'].append(index+1)
        if previous['flow_parts'][-1]['columns']==segment['columns']:
            previous['flow_parts'][-1]['nodes'].extend(segment['nodes']);previous['flow_parts'][-1]['source_sections'].append(index+1)
        else:previous['flow_parts'].extend(segment['flow_parts'])
    return result
