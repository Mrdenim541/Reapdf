"""Explicit Word section columns, flowing top-to-bottom then left-to-right."""
import math
import pymupdf as f
from .engine import DocumentError
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def parse(section,width):
    node=section.find(W+'cols')
    if node is None:return {'widths':[width],'gaps':[],'separator':False}
    def integer(value,default):
        try:return int(default if value is None else value)
        except (ValueError,TypeError):raise DocumentError('Columnas Word: dimensiones o cantidad no válidas.')
    equal=node.attrib.get(W+'equalWidth','1')
    if equal not in ['1','true','on','0','false','off']:raise DocumentError('Columnas Word: equalWidth no válido.')
    children=node.findall(W+'col');count=integer(node.attrib.get(W+'num'),len(children) if children else 1)
    if not 1<=count<=4 or len(children)>4:raise DocumentError('Se admiten de una a cuatro columnas Word por sección.')
    if section.find(W+'bidi') is not None:raise DocumentError('Las columnas de derecha a izquierda requieren otro tratamiento.')
    if equal in ['1','true','on']:
        gap=integer(node.attrib.get(W+'space'),720)/20
        widths=[(width-gap*(count-1))/count]*count;gaps=[gap]*(count-1)
    else:
        if len(children)!=count:raise DocumentError('Define el ancho de todas las columnas Word desiguales.')
        widths=[integer(c.attrib.get(W+'w'),0)/20 for c in children]
        gaps=[integer(c.attrib.get(W+'space'),0)/20 for c in children[:-1]]
        if abs(sum(widths)+sum(gaps)-width)>1:raise DocumentError('Los anchos y espacios de las columnas Word no coinciden con el área de texto.')
    if any(not math.isfinite(v) or v<0 for v in widths+gaps) or min(widths)<72:raise DocumentError('Cada columna Word necesita al menos 72 pt de ancho y espacios no negativos.')
    return {'widths':widths,'gaps':gaps,'separator':node.attrib.get(W+'sep','0') in ['1','true','on']}


def frame(columns,index,width,height,left,top,right,bottom,reserve=0):
    count=len(columns['widths']);column=index%count
    x=left+sum(columns['widths'][:column])+sum(columns['gaps'][:column])
    return (f.Rect(0,0,width,height) if column==0 else None),f.Rect(x,top,x+columns['widths'][column],height-bottom-reserve),None


def separators(doc,columns,top,bottom,reserves,heights=None):
    if not columns['separator'] or len(columns['widths'])==1:return
    # x positions are relative to the left text margin; caller supplies it.
    left=columns['left'];positions=[];x=left
    for width,gap in zip(columns['widths'],columns['gaps']):
        x+=width;positions.append(x+gap/2);x+=gap
    for number,page in enumerate(doc):
        y1=page.rect.height-bottom-reserves.get(number,0)
        if heights and number in heights:y1=min(y1,top+heights[number])
        for x in positions:page.draw_line((x,top),(x,y1),color=(.25,.25,.25),width=.5)
