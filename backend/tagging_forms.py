"""Audit text-only Form invocations for an enclosing page MCID.

Each occurrence is one reviewed semantic unit. Internal streams/resources are
never rewritten or shared between semantic identities. Mixed/marked Forms stay
protected; this is not arbitrary internal MCID repair.
"""
import pymupdf as f
from .engine import DocumentError
from .pdf_content import operations
from .styled_text import stream
from .text_compositing import graphics,group


def audit(doc,target,budget=None,path=()):
    budget={'nodes':0,'bytes':0} if budget is None else budget
    def fail():raise DocumentError('El Form contiene imágenes, marcas, estados o referencias que requieren etiquetado especializado.')
    if target in path or len(path)>=8:fail()
    budget['nodes']+=1
    if budget['nodes']>200:raise DocumentError('El etiquetado supera 200 invocaciones Form.')
    if doc.xref_get_key(target,'Subtype')!=('name','/Form') or not group(doc,target):fail()
    if any(doc.xref_get_key(target,k)[0]!='null' for k in ['StructParents','StructParent','OC','Ref','Resources/Properties']):fail()
    if doc.xref_get_key(target,'Resources')[0] not in ['dict','xref']:fail()
    data=stream(doc,target,16*1024*1024);budget['bytes']+=len(data)
    if budget['bytes']>32*1024*1024:raise DocumentError('El etiquetado Form supera 32 MB.')
    graphics(doc,target,data);text=False
    for op,args,token in operations(data):
        if op in ['BMC','BDC','EMC','MP','DP']:fail()
        if op in ['Tj','TJ',"'",'"']:text=True
        if op=='Do':
            if len(args)!=1 or args[0].kind!='name':fail()
            kind,value=doc.xref_get_key(target,'Resources/XObject/'+args[0].value)
            if kind!='xref':fail()
            text=audit(doc,int(value.split()[0]),budget,(*path,target)) or text
    if not text:fail()
    return text
