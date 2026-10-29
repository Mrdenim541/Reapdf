"""Bounded OOXML field normalization and a page-number whitelist; no code execution."""
from copy import deepcopy
import re
from xml.etree import ElementTree as E
from .engine import DocumentError
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
PREFIX='REAPDF_FIELD_041_'
def tag(name):return '{'+W+'}'+name


def normalize_fields(root):
    complex_nodes=set();forced_cached=set();char_formats={};count=0;units=0
    for parent in reversed(list(root.iter())):
        if parent.tag not in {tag('p'),tag('hyperlink'),tag('fldSimple')}:continue
        output=[];stack=[]
        def emit(node):
            if not stack:output.append(node)
            elif stack[-1]['separated']:stack[-1]['cache'].append(node)
        for child in list(parent):
            pieces=[]
            if child.tag==tag('r') and any(n.tag in {tag('fldChar'),tag('instrText')} for n in child):
                props=child.find(tag('rPr'))
                if props is not None and len(props)>50:raise DocumentError('Demasiadas propiedades en un fragmento de campo Word.')
                for item in child:
                    if item.tag==tag('rPr'):continue
                    if item.tag in {tag('fldChar'),tag('instrText')}:pieces.append((item.tag,item,props))
                    else:
                        run=E.Element(tag('r'))
                        if props is not None:run.append(deepcopy(props))
                        run.append(deepcopy(item));pieces.append(('visible',run,None))
            else:pieces=[('visible',child,None)]
            for kind,node,run_props in pieces:
                units+=1
                if units>50000:raise DocumentError('Los campos Word superan 50000 elementos normalizados.')
                if kind==tag('fldChar'):
                    action=node.attrib.get(tag('fldCharType'))
                    if action=='begin':
                        if len(stack)>=16:raise DocumentError('Los campos Word superan 16 niveles anidados.')
                        if stack and not stack[-1]['separated']:stack[-1]['nested_instruction']=True
                        stack.append({'instruction':[],'cache':[],'separated':False,'nested_instruction':False,'properties':run_props,'code_seen':False,'code_properties':None})
                    elif action=='separate':
                        if not stack or stack[-1]['separated']:raise DocumentError('Campo Word con separador sin inicio o repetido.')
                        stack[-1]['separated']=True
                    elif action=='end':
                        if not stack:raise DocumentError('Campo Word con cierre sin inicio.')
                        frame=stack.pop();instruction=''.join(frame['instruction'])
                        if len(instruction)>2000:raise DocumentError('Una instrucción de campo Word supera 2000 caracteres.')
                        field=E.Element(tag('fldSimple'),{tag('instr'):instruction});field.extend(frame['cache'])
                        if not frame['cache'] and frame['properties'] is not None:
                            run=E.SubElement(field,tag('r'));run.append(deepcopy(frame['properties']));E.SubElement(run,tag('t'))
                        complex_nodes.add(field)
                        if 'CHARFORMAT' in instruction.upper().split():char_formats[field]=frame['code_properties']
                        if frame['nested_instruction']:forced_cached.add(field)
                        count+=1
                        if count>500:raise DocumentError('Hasta 500 campos complejos por parte Word.')
                        emit(field)
                    else:raise DocumentError('Tipo de límite de campo Word no compatible.')
                elif kind==tag('instrText'):
                    if not stack or stack[-1]['separated']:raise DocumentError('Instrucción Word fuera de un campo completo.')
                    if not stack[-1]['code_seen'] and (node.text or '').strip():
                        stack[-1]['code_seen']=True;stack[-1]['code_properties']=deepcopy(run_props) if run_props is not None else None
                    stack[-1]['instruction'].append(node.text or '')
                else:emit(node)
        if stack:raise DocumentError('El encabezado/pie contiene un campo Word sin cerrar.')
        parent[:]=output
    return root,complex_nodes,forced_cached,char_formats


def page_instruction(value):
    parts=(value or '').split()
    if not parts or parts[0].upper() not in ['PAGE','NUMPAGES','SECTIONPAGES'] or len(parts)>15:return None
    fmt=None
    for i in range(1,len(parts),2):
        if i+1>=len(parts) or parts[i]!='\\*':return None
        switch=parts[i+1]
        if switch.upper() in ['MERGEFORMAT','CHARFORMAT']:continue
        choice={'ROMAN':'upperRoman','roman':'lowerRoman','ALPHABETIC':'upperLetter','alphabetic':'lowerLetter'}.get(switch)
        if switch.upper()=='ARABIC':choice='decimal'
        if choice is None or fmt is not None:return None
        fmt=choice
    return parts[0].upper(),fmt


def number_label(value,fmt):
    if type(value) is not int or value<1:raise DocumentError('Número de página Word no válido.')
    if fmt=='decimal':return str(value)
    if fmt in ['upperLetter','lowerLetter'] and value<=18278:
        out=''
        while value:value,rem=divmod(value-1,26);out=chr(97+rem)+out
        return out.upper() if fmt=='upperLetter' else out
    if fmt in ['upperRoman','lowerRoman'] and value<=3999:
        out=''
        for amount,symbol in [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
            count,value=divmod(value,amount);out+=symbol*count
        return out if fmt=='upperRoman' else out.lower()
    raise DocumentError('Numeración Word fuera del formato compatible: romanos hasta 3999 y letras hasta 18278.')


class PageFields:
    def __init__(self):self.entries=[];self.start=1;self.format='decimal'
    def configure(self,section):
        node=section.find(tag('pgNumType')) if section is not None else None
        if node is None:return
        raw=node.attrib.get(tag('start'),'1');fmt=node.attrib.get(tag('fmt'),'decimal')
        if not re.fullmatch('[0-9]{1,4}',raw) or not 1<=int(raw)<=9999 or fmt not in ['decimal','upperRoman','lowerRoman','upperLetter','lowerLetter']:raise DocumentError('Numeración de sección Word no compatible: inicio 1–9999 y formato decimal, romano o alfabético.')
        self.start=int(raw);self.format=fmt;number_label(self.start,fmt)
    def register(self,instruction):
        parsed=page_instruction(instruction)
        if parsed is None:return None
        if len(self.entries)>=500:raise DocumentError('Hasta 500 campos de página por documento Word.')
        token=PREFIX+str(len(self.entries))+'_VALUE';self.entries.append((token,*parsed));return token
    def replace(self,content,page,total,measure=False,section_total=None):
        for token,command,override in self.entries:
            if token not in content:continue
            fmt=override or (self.format if command=='PAGE' else 'decimal')
            if measure:
                lengths=[]
                for n in range(50):
                    try:lengths.append(len(number_label(self.start+n if command=='PAGE' else n+1,fmt)))
                    except DocumentError:continue
                if not lengths:raise DocumentError('No se puede medir la numeración Word compatible.')
                label='W'*max(lengths)  # Conservative width; rendering validates the actual values again.
            else:label=number_label(self.start+page-1 if command=='PAGE' else (section_total if command=='SECTIONPAGES' and section_total is not None else total),fmt)
            content=content.replace(token,label)
        return content
