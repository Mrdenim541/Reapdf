"""Explicit DOCX body bookmark identities for native internal PDF links."""
import hashlib,re
from .engine import DocumentError
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


class Bookmarks:
    def __init__(self,body):
        self.names={};self.identities={};ends=[];self.links=0;self.nodes=set();self.skipped=0
        referenced={node.attrib.get(W+'anchor') for node in body.iter() if node.tag==W+'hyperlink'}
        for node in body.iter():
            if node.tag==W+'bookmarkStart':
                name=node.attrib.get(W+'name','');identity=node.attrib.get(W+'id','')
                if not name or len(name)>200 or any(ord(c)<32 for c in name) or not re.fullmatch(r'\d{1,10}',identity) or name in self.names or identity in self.identities:
                    raise DocumentError('Los marcadores Word necesitan nombres e identidades únicos y compatibles.')
                if len(self.names)>=500:raise DocumentError('Hasta 500 marcadores internos Word por documento.')
                self.names[name]='REAPDF_BOOKMARK_'+hashlib.sha256(name.encode()).hexdigest()
                self.identities[identity]=name
                self.nodes.add(node)
            elif node.tag==W+'bookmarkEnd':ends.append(node.attrib.get(W+'id',''))
        if len(ends)!=len(set(ends)):raise DocumentError('Los marcadores Word tienen finales repetidos.')
        for identity,name in list(self.identities.items()):
            if identity not in ends:
                if name in referenced:raise DocumentError('El destino del enlace Word no tiene un marcador cerrado.')
                del self.names[name];del self.identities[identity];self.skipped+=1

    def destination(self,node):
        name=node.attrib.get(W+'name');identity=node.attrib.get(W+'id')
        if node in self.nodes and self.identities.get(identity)==name:return '<a id="'+self.names[name]+'"></a>'
        return ''

    def target(self,name):return self.names.get(name)
