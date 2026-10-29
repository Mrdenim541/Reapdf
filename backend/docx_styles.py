"""Bounded Word style inheritance and explicit, conservative list numbering."""
from copy import deepcopy
import re
from xml.etree import ElementTree as E
from .engine import DocumentError

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def tag(name):return '{'+W+'}'+name
def val(node,default=None):return node.attrib.get(tag('val'),default) if node is not None else default

def merged(*nodes):
    result={}
    for node in nodes:
        if node is not None:
            for child in node:
                old=result.get(child.tag)
                # Paragraph properties such as numPr, spacing and ind inherit
                # individual attributes/children, not the entire container.
                if old is not None:
                    child=deepcopy(child);child.attrib={**old.attrib,**child.attrib}
                    existing={c.tag for c in child}
                    for c in old:
                        if c.tag not in existing:child.append(deepcopy(c))
                result[child.tag]=child
    return result

def element(properties):
    node=E.Element(tag('properties'))
    node.extend(deepcopy(list(properties.values())));return node

class WordStyles:
    def __init__(self,styles,numbering,warnings):
        self.warnings=warnings;self.styles={};self.defaults={};self.cache={};self.used=set();self.list_items=0
        self.pdefault=self.rdefault=None;self.abstract={};self.nums={};self.counters={}
        if styles is not None:
            self.pdefault=styles.find(tag('docDefaults')+'/'+tag('pPrDefault')+'/'+tag('pPr'))
            self.rdefault=styles.find(tag('docDefaults')+'/'+tag('rPrDefault')+'/'+tag('rPr'))
            for style in styles.findall(tag('style')):
                ident=style.attrib.get(tag('styleId'));kind=style.attrib.get(tag('type'))
                if not ident or ident in self.styles or len(self.styles)>=1000:raise DocumentError('Estilos Word repetidos, sin identificador o más de 1000.')
                self.styles[ident]=style
                if style.attrib.get(tag('default')) in ['1','true']:
                    if kind in self.defaults:raise DocumentError('Estilos predeterminados Word repetidos.')
                    self.defaults[kind]=ident
        if numbering is not None:
            for node in numbering:
                if node.tag not in {tag('abstractNum'),tag('num')}:continue
                target=self.abstract if node.tag==tag('abstractNum') else self.nums
                ident=node.attrib.get(tag('abstractNumId') if target is self.abstract else tag('numId'))
                if ident is None or ident in target or len(target)>=1000:raise DocumentError('Numeraciones Word repetidas o fuera de límites.')
                target[ident]=node

    def chain(self,ident,kind,path=()):
        if not ident:return []
        if ident in path or len(path)>=32:raise DocumentError('Los estilos Word tienen un ciclo o más de 32 niveles de herencia.')
        key=(ident,kind)
        if key in self.cache:return self.cache[key]
        style=self.styles.get(ident)
        if style is None or style.attrib.get(tag('type'))!=kind:
            self.warnings.add('Estilo Word ausente o de tipo incompatible: se utiliza formato básico.');return []
        self.used.add(ident)
        chain=self.chain(val(style.find(tag('basedOn'))),kind,path+(ident,))+[style]
        if len(chain)>32:raise DocumentError('Los estilos Word superan 32 niveles de herencia.')
        self.cache[key]=chain;return chain

    def paragraph(self,node):
        direct=node.find(tag('pPr'));ident=val(direct.find(tag('pStyle'))) if direct is not None else None
        chain=self.chain(ident or self.defaults.get('paragraph'),'paragraph')
        p=merged(self.pdefault,*(s.find(tag('pPr')) for s in chain),direct)
        r=self.style_runs(self.rdefault,chain)
        return element(p),element(r)

    def style_runs(self,inherited,chain):
        # Toggle properties in styles invert the inherited state when enabled;
        # false in a style does not disable an inherited toggle (OOXML 17.7.3).
        result=merged(inherited)
        for style in chain:
            props=style.find(tag('rPr'));next_props=merged(element(result),props)
            if props is not None:
                for name in ['b','i','strike']:
                    toggle=props.find(tag(name))
                    if toggle is None:continue
                    previous=result.get(tag(name));enabled=previous is not None and val(previous,'1') not in ['0','false','off']
                    if val(toggle,'1') not in ['0','false','off']:enabled=not enabled
                    replacement=deepcopy(toggle);replacement.set(tag('val'),'1' if enabled else '0');next_props[tag(name)]=replacement
            result=next_props
        return result

    def run(self,node,inherited):
        direct=node.find(tag('rPr'));ident=val(direct.find(tag('rStyle'))) if direct is not None else None
        chain=self.chain(ident or self.defaults.get('character'),'character')
        return element(merged(element(self.style_runs(inherited,chain)),direct))

    def marker(self,props):
        num=props.find(tag('numPr'))
        if num is None:return '',0
        ident=val(num.find(tag('numId')));level=val(num.find(tag('ilvl')),'0')
        if ident=='0':return '',0
        def unsupported():
            self.warnings.add('La numeración/listas no compatible se omite; revisa los párrafos afectados.');return '',0
        if ident not in self.nums or not re.fullmatch('[0-8]',level or ''):return unsupported()
        definition=self.nums[ident];abstract=self.abstract.get(val(definition.find(tag('abstractNumId'))))
        if abstract is None or abstract.find(tag('numStyleLink')) is not None or abstract.find(tag('styleLink')) is not None:return unsupported()
        level_nodes=abstract.findall(tag('lvl'))
        levels={n.attrib.get(tag('ilvl')):n for n in level_nodes}
        if len(levels)!=len(level_nodes):raise DocumentError('Niveles de numeración Word repetidos.')
        # Overrides with full definitions are supported; unsupported restart
        # semantics are never silently converted to a different list.
        starts={};overrides=set()
        for override in definition.findall(tag('lvlOverride')):
            key=override.attrib.get(tag('ilvl'));replacement=override.find(tag('lvl'))
            if key in overrides:raise DocumentError('Excepciones de numeración Word repetidas.')
            overrides.add(key)
            if replacement is not None:levels[key]=replacement
            start=val(override.find(tag('startOverride')))
            if start is not None:starts[key]=start
        current=levels.get(level)
        if current is None or any(n.find(tag('lvlRestart')) is not None or n.find(tag('isLgl')) is not None for n in levels.values()):return unsupported()
        fmt=val(current.find(tag('numFmt')),'decimal');template=val(current.find(tag('lvlText')))
        if fmt not in ['decimal','bullet','lowerLetter','upperLetter','lowerRoman','upperRoman'] or not template or len(template)>100:return unsupported()
        counters=self.counters.setdefault(ident,{})
        def start_value(key):
            raw=starts.get(key,val(levels[key].find(tag('start')),'1'))
            if not re.fullmatch('[0-9]{1,4}',raw or ''):raise DocumentError('Inicio de numeración Word fuera de 0–9999.')
            return int(raw)
        depth=int(level)
        # Validate all referenced levels before changing state.
        references=re.findall(r'%([1-9])',template) if fmt!='bullet' else []
        if any(str(int(k)-1) not in levels or int(k)-1>depth for k in references):return unsupported()
        for key in references+[str(depth+1)]:
            idx=str(int(key)-1);start_value(idx)
        counters[level]=counters.get(level,start_value(level)-1)+1
        for key in list(counters):
            if int(key)>depth:del counters[key]
        def render(key):
            idx=str(int(key)-1);value=counters.get(idx,start_value(idx));kind=val(levels[idx].find(tag('numFmt')),'decimal')
            if kind=='decimal':return str(value)
            if kind in ['lowerLetter','upperLetter'] and 1<=value<=18278:
                out=''
                while value:value,rem=divmod(value-1,26);out=chr(97+rem)+out
                return out.upper() if kind=='upperLetter' else out
            if kind in ['lowerRoman','upperRoman'] and 1<=value<=3999:
                out=''
                for amount,symbol in [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
                    count,value=divmod(value,amount);out+=symbol*count
                return out.lower() if kind=='lowerRoman' else out
            raise DocumentError('Valor o formato de numeración Word no compatible.')
        self.list_items+=1
        if fmt=='bullet':
            if template in ['•','·','○','▪','-','–']:return template,depth
            self.warnings.add('Viñeta con fuente especial sustituida por un punto estándar.')
            return '•',depth
        return re.sub(r'%([1-9])',lambda m:render(m[1]),template),depth
